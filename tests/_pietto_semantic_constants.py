"""Shared source of the single-file top-level constant tests: a shape, one
constant of each type and a query that reads each of them."""

from __future__ import annotations

from pietto.ast_nodes import Script
from pietto.parser_api import parse_source

SHAPE = """shape Event:
    id: Int
    day: Date
    at: Timestamp
    note: Text
    paid: Bool
    amount: Float

source events: Event = {dialect}.table("events")

"""
FIRST = SHAPE.count("\n") + 1
CONSTANTS = """cutoff: Date = "2024-01-31"

stamp: Timestamp = "2024-01-31 08:30:00.25"

label: Text = "it's \\\\ ok"

flag: Bool = True

limit_n: Int = 3

lo: Float = -1.5

"""
QUERY = """def above(x: Float) -> Bool: return x > lo

query q:
    from events
    let moved = amount + lo
    where day <= cutoff and at < stamp and paid == flag and above(amount)
    select:
        id
        as_of = cutoff
        stamped = stamp
        tag = label
        on = flag
        shifted = moved
        same_day = date_of(at) == cutoff
        later = any(e.day > cutoff for e in events)
    order by id
    limit limit_n
"""


def parsed(source: str) -> Script:
    parsed = parse_source(source, path="constants.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    return parsed.ast
