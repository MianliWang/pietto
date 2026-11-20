"""Deterministic, bounded shrinking of generated cases.

``shrink`` reduces a case of tests/_pietto_harness_generated_forms.py for
which a caller's ``fails`` holds to a smaller case for which it still holds.
It tries the ``candidates`` of the current case in a fixed order, takes the
first that still fails and starts again from it, and stops when no candidate
fails or after ``budget`` calls of ``fails``. Every candidate is strictly
smaller by ``size``, so the steps end on their own too. Nothing is drawn at
random and no set orders anything, so the same case and predicate always
give the same result.

Each candidate stays in the generator's range: it drops the LIMIT, the WHERE,
a select item, a GROUP BY key, a ``let`` that nothing reads, an order key, a
top-level conjunct of a JOIN ``on`` or a field that nothing reads, or lifts
an operand of a unary ``-``, arithmetic, a call, ``and`` or ``or`` into its
place, which has the same type. It keeps ``id``, one other field, one select
item, one aggregate and the final ``id`` order key of a row or JOIN form,
leaves no LIMIT on an aggregate without keys, and lifts nothing out of an
``or`` in a JOIN ``on``, where a top-level ``Float`` comparison or ``is not
None`` conjunct could be refused in a project. ``fails`` should still match
the original failure's signature, not any failure.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator
from dataclasses import replace

from _pietto_harness_generated_forms import Case

BUDGET = 1000  # calls of ``fails`` in one shrink
_LIFTED = ("neg", "arith", "call", "bool")


def shrink(case: Case, fails: Callable[[Case], bool], budget: int = BUDGET) -> Case:
    """The smallest case reached from failing ``case`` that still ``fails``."""
    calls = 0
    while True:
        for candidate in candidates(case):
            if calls == budget:
                return case
            calls += 1
            if fails(candidate):
                case = candidate
                break
        else:
            return case


def _walk(expression: tuple) -> Iterator[tuple]:
    yield expression
    for part in expression[1:]:
        if isinstance(part, tuple):
            yield from _walk(part)


def _expressions(case: Case) -> list[tuple]:
    on = case.join[1] if case.join else None
    parts = [on, case.where, *(value for _, value in case.lets)]
    return [e for e in parts + [e for _, e in case.items] if e is not None]


def size(case: Case) -> int:
    """Expression nodes plus fields, lets, items, keys, order keys and LIMIT."""
    nodes = sum(1 for e in _expressions(case) for _ in _walk(e))
    parts = (case.fields, case.lets, case.items, case.keys, case.order)
    return nodes + sum(map(len, parts)) + (case.limit is not None)


def _lifts(node: tuple, on: bool = False) -> Iterator[tuple]:
    """``node`` with one operand lifted into its operator's place."""
    if (node[:2] == ("bool", "and")) if on else (node[0] in _LIFTED):
        yield from (part for part in node[1:] if isinstance(part, tuple))
    for index, part in enumerate(node):
        if isinstance(part, tuple):
            for lifted in _lifts(part, on):
                yield node[:index] + (lifted,) + node[index + 1 :]


def _without(items: tuple, index: int) -> tuple:
    return items[:index] + items[index + 1 :]


def candidates(case: Case) -> Iterator[Case]:
    """Each one-step reduction of ``case``, coarsest first, in a fixed order."""
    if case.limit is not None:
        yield replace(case, limit=None)
    if case.where is not None:
        yield replace(case, where=None)
    aggregates = sum(expression[0] == "agg" for _, expression in case.items)
    for index, (name, expression) in enumerate(case.items):
        if case.form == "aggregate" and name in case.keys:
            keys = tuple(key for key in case.keys if key != name)
            yield replace(
                case,
                keys=keys,
                items=_without(case.items, index),
                order=tuple(entry for entry in case.order if entry[0] != name),
                limit=case.limit if keys else None,
            )
        elif len(case.items) > 1 and (expression[0] != "agg" or aggregates > 1):
            yield replace(case, items=_without(case.items, index))
    nodes = [node for e in _expressions(case) for node in _walk(e)]
    for index, (name, _) in enumerate(case.lets):
        if ("let", name) not in nodes:
            yield replace(case, lets=_without(case.lets, index))
    for index in range(len(case.order) - (case.form != "aggregate")):
        yield replace(case, order=_without(case.order, index))
    kind, on = case.join or ("", None)
    if on is not None:
        yield from (replace(case, join=(kind, c)) for c in _lifts(on, on=True))
    if case.where is not None:
        yield from (replace(case, where=c) for c in _lifts(case.where))
    for index, (name, value) in enumerate(case.lets):
        for lifted in _lifts(value):
            lets = case.lets[:index] + ((name, lifted),) + case.lets[index + 1 :]
            yield replace(case, lets=lets)
    for index, (name, expression) in enumerate(case.items):
        for lifted in _lifts(expression):
            items = case.items[:index] + ((name, lifted),) + case.items[index + 1 :]
            yield replace(case, items=items)
    read = [node[1] for node in nodes if node[0] == "field"]
    read += [*case.keys, *(key for key, _ in case.order)]
    read = [name.rpartition(".")[2] for name in read]
    if len(case.fields) > 2:
        for index, (name, _, _) in enumerate(case.fields[1:], 1):
            if name not in read:
                yield replace(case, fields=_without(case.fields, index))
