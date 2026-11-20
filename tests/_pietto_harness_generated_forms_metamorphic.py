"""Metamorphic relations over the generated opened forms.

Each relation rewrites a case of tests/_pietto_harness_generated_forms.py
into one that means the same and states, with no oracle, what the product's
public outputs of the two must share:

- ``layout``: comment lines, a WHERE broken over lines inside parentheses
  with a comment, and doubled parentheses around every value ``let``, SELECT
  expression and JOIN ``on``. Everything is kept, each SQL byte for byte.
- ``rename``: value ``let`` ``l<i>`` becomes ``v<i>`` (a SELECT item keeps
  its output name) and the JOIN binding ``r`` becomes ``s``. Everything is
  kept, except that the SQL quotes ``s`` where it quoted ``r``.
- ``inline``: a SELECT item that reads a value ``let`` writes the ``let``'s
  expression instead, and the ``let`` goes, since a SELECT output may not
  take a ``let``'s name (PIE-S2329). All but a project's SQL is kept: a
  project computes a ``let`` in an earlier step.
- ``reverse``: the SELECT items and the value ``let``s in reverse order. The
  columns come in reverse order; the SQL is not compared.
- ``commute``: the operands of ``and``, ``or``, ``==``, ``!=``, ``+`` and
  ``*`` swapped, and ``<``, ``<=``, ``>``, ``>=`` mirrored, everywhere. All
  but the SQL is kept.
- ``duplicate``: a WHERE ``p`` becomes ``p and p`` and a JOIN ``on c``
  becomes ``on c and c``. All but the SQL is kept.

``reverse``, ``commute`` and ``duplicate`` compare no SQL, so they catch a
rewrite only where it changes acceptance, codes, types or nullability; no
relation compares rows.
"""

from __future__ import annotations

from dataclasses import replace
import re

import _pietto_harness_generated_forms as forms

RELATIONS = ("layout", "rename", "inline", "reverse", "commute", "duplicate")
_MIRROR = {"==": "==", "!=": "!=", "<": ">", "<=": ">=", ">": "<", ">=": "<="}


def _commute(expression: tuple) -> tuple:
    tag = expression[0]
    parts = tuple(
        _commute(part) if isinstance(part, tuple) else part for part in expression
    )
    if tag in ("bool", "cmp") or tag == "arith" and expression[1] in ("+", "*"):
        return (tag, _MIRROR.get(expression[1], expression[1]), parts[3], parts[2])
    return parts


def rewrite(case: forms.Case, relation: str) -> forms.Case:
    """The case that ``relation`` makes of ``case``; ``layout`` and the JOIN
    binding of ``rename`` change only the text (``module_text``)."""
    if relation == "rename":
        lets = tuple(("v" + name[1:], value) for name, value in case.lets)
        items = tuple(
            (output, ("let", "v" + read[1][1:]) if read[0] == "let" else read)
            for output, read in case.items
        )
        return replace(case, lets=lets, items=items)
    if relation == "inline":
        values = dict(case.lets)
        read = {expression[1] for _, expression in case.items if expression[0] == "let"}
        items = tuple(
            (output, values[expression[1]] if expression[0] == "let" else expression)
            for output, expression in case.items
        )
        lets = tuple((name, value) for name, value in case.lets if name not in read)
        return replace(case, lets=lets, items=items)
    if relation == "reverse":
        return replace(case, lets=case.lets[::-1], items=case.items[::-1])
    if relation == "commute":
        join = case.join and (case.join[0], case.join[1] and _commute(case.join[1]))
        return replace(
            case,
            join=join,
            lets=tuple((name, _commute(value)) for name, value in case.lets),
            where=case.where and _commute(case.where),
            items=tuple((name, _commute(value)) for name, value in case.items),
        )
    if relation == "duplicate":
        join = case.join
        if join is not None and join[1] is not None:
            join = (join[0], ("bool", "and", join[1], join[1]))
        where = case.where and ("bool", "and", case.where, case.where)
        return replace(case, join=join, where=where)
    if relation == "layout":
        return case
    raise ValueError(relation)


def _layout(text: str) -> str:
    lines = ["# The same query, laid out differently."]
    for line in text.splitlines():
        head, equals, tail = line.partition(" = ")
        if line.startswith("    where "):
            lines += ["    where (", f"        {line[10:]}  # a comment", "    )"]
        elif " join " in line and " on " in line:
            head, _, on = line.partition(" on ")
            lines.append(f"{head} on (({on}))")
        elif (
            equals
            and line != "    let r = u"
            and line.startswith(("    let ", "        "))
        ):
            lines.append(f"{head} = (({tail}))")
        else:
            lines.append(line)
        if line == "query q:":
            lines.append("    # a comment line in the block")
    return "\n".join(lines) + "\n"


def module_text(case: forms.Case, relation: str, target: str) -> str:
    """The module of ``relation``'s rewrite of ``case`` for ``target``."""
    text = forms.module_text(rewrite(case, relation), target)
    if relation == "layout":
        return _layout(text)
    if relation == "rename":
        head, query, body = text.partition("query q:")
        return head + query + re.sub(r"\br\b", "s", body)
    return text
