"""The range proof of SQLite `Int` arithmetic (S14; the lead's L1 A).

SQLite turns an `Int` result outside signed 64 bits into a `REAL` without
an error, so the adapter admits `+`, `-`, `*`, unary `-` and `abs` only when
the bounds of every result lie inside them. A field read's bounds are its
contract `int_range`, each read on its own, and a literal's its value; each
operation's bounds follow from its operands' alone, so `x * x` over a range
of both signs has a negative lower bound. This module holds the bounds of
each operation and imports nothing from the pipeline.
"""

from __future__ import annotations

__all__: tuple[str, ...] = ()

MIN_INT, MAX_INT = -(2**63), 2**63 - 1

type Bounds = tuple[int, int]


def combine(operator: str, operands: tuple[Bounds, ...]) -> Bounds:
    """The exact bounds of `operator` (`+`, `-`, `*`, `abs`, or `-` over one
    operand) over operands within their bounds."""
    if operator == "abs":
        ((low, high),) = operands
        return max(low, -high, 0), max(-low, high)
    if len(operands) == 1:
        ((low, high),) = operands
        return -high, -low
    (a, b), (c, d) = operands
    if operator == "+":
        return a + c, b + d
    if operator == "-":
        return a - d, b - c
    assert operator == "*"
    products = (a * c, a * d, b * c, b * d)
    return min(products), max(products)


def inside(bounds: Bounds) -> bool:
    return MIN_INT <= bounds[0] and bounds[1] <= MAX_INT
